"""Tool execution helpers for cihub ci."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET
import yaml

from cihub.cli import resolve_executable


@dataclass
class ToolResult:
    tool: str
    ran: bool
    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "ran": self.ran,
            "success": self.success,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> ToolResult:
        return cls(
            tool=str(data.get("tool", "")),
            ran=bool(data.get("ran", False)),
            success=bool(data.get("success", False)),
            metrics=dict(data.get("metrics", {}) or {}),
            artifacts=dict(data.get("artifacts", {}) or {}),
        )

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_payload(), indent=2), encoding="utf-8")


def _run_command(
    cmd: list[str],
    workdir: Path,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    resolved = [resolve_executable(cmd[0]), *cmd[1:]]
    venv_root = os.environ.get("VIRTUAL_ENV")
    venv_bin = None
    if venv_root:
        venv_bin = Path(venv_root) / ("Scripts" if os.name == "nt" else "bin")
    elif sys.prefix != sys.base_prefix:
        venv_bin = Path(sys.executable).parent
    if venv_bin:
        candidate = venv_bin / cmd[0]
        if os.name == "nt" and not candidate.suffix:
            candidate = candidate.with_suffix(".exe")
        if candidate.exists():
            resolved[0] = str(candidate)
    return subprocess.run(  # noqa: S603
        resolved,
        cwd=workdir,
        env=env or os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _parse_junit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "tests_runtime_seconds": 0.0,
        }
    root = ET.parse(path).getroot()
    if root.tag.endswith("testsuites"):
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
        for suite in root:
            totals["tests"] += int(suite.attrib.get("tests", 0))
            totals["failures"] += int(suite.attrib.get("failures", 0))
            totals["errors"] += int(suite.attrib.get("errors", 0))
            totals["skipped"] += int(suite.attrib.get("skipped", 0))
            totals["time"] += float(suite.attrib.get("time", 0.0))
    else:
        totals = {
            "tests": int(root.attrib.get("tests", 0)),
            "failures": int(root.attrib.get("failures", 0)),
            "errors": int(root.attrib.get("errors", 0)),
            "skipped": int(root.attrib.get("skipped", 0)),
            "time": float(root.attrib.get("time", 0.0)),
        }
    failed = totals["failures"] + totals["errors"]
    passed = max(totals["tests"] - failed - totals["skipped"], 0)
    return {
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_skipped": totals["skipped"],
        "tests_runtime_seconds": totals["time"],
    }


def _parse_coverage(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "coverage": 0,
            "coverage_lines_covered": 0,
            "coverage_lines_total": 0,
        }
    root = ET.parse(path).getroot()
    line_rate = float(root.attrib.get("line-rate", 0))
    lines_covered = int(root.attrib.get("lines-covered", 0))
    lines_total = int(root.attrib.get("lines-valid", root.attrib.get("lines-total", 0)))
    coverage = int(round(line_rate * 100))
    return {
        "coverage": coverage,
        "coverage_lines_covered": lines_covered,
        "coverage_lines_total": lines_total,
    }


def _parse_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(data, (dict, list)):
        return data
    return None


def _find_files(workdir: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(workdir.rglob(pattern))
    unique = {path.resolve() for path in files}
    return sorted(unique, key=lambda path: str(path))


def _parse_junit_files(paths: list[Path]) -> dict[str, Any]:
    totals = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_runtime_seconds": 0.0,
    }
    for path in paths:
        parsed = _parse_junit(path)
        totals["tests_passed"] += int(parsed.get("tests_passed", 0))
        totals["tests_failed"] += int(parsed.get("tests_failed", 0))
        totals["tests_skipped"] += int(parsed.get("tests_skipped", 0))
        totals["tests_runtime_seconds"] += float(parsed.get("tests_runtime_seconds", 0.0) or 0.0)
    return totals


def _parse_jacoco_files(paths: list[Path]) -> dict[str, Any]:
    covered = 0
    missed = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for counter in root.iter("counter"):
            if counter.attrib.get("type") != "LINE":
                continue
            covered += int(counter.attrib.get("covered", 0))
            missed += int(counter.attrib.get("missed", 0))
    total = covered + missed
    coverage = int(round((covered / total) * 100)) if total else 0
    return {
        "coverage": coverage,
        "coverage_lines_covered": covered,
        "coverage_lines_total": total,
    }


def _parse_pitest_files(paths: list[Path]) -> dict[str, Any]:
    killed = 0
    survived = 0
    no_coverage = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for mutation in root.iter("mutation"):
            status = mutation.attrib.get("status")
            if status == "KILLED":
                killed += 1
            elif status == "SURVIVED":
                survived += 1
            elif status == "NO_COVERAGE":
                no_coverage += 1
    total = killed + survived + no_coverage
    score = int(round((killed / total) * 100)) if total else 0
    return {
        "mutation_score": score,
        "mutation_killed": killed,
        "mutation_survived": survived,
    }


def _parse_checkstyle_files(paths: list[Path]) -> dict[str, Any]:
    violations = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        violations += len(list(root.iter("error")))
    return {"checkstyle_issues": violations}


def _parse_spotbugs_files(paths: list[Path]) -> dict[str, Any]:
    issues = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        issues += len(list(root.iter("BugInstance")))
    return {"spotbugs_issues": issues}


def _parse_pmd_files(paths: list[Path]) -> dict[str, Any]:
    violations = 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        violations += len(list(root.iter("violation")))
    return {"pmd_violations": violations}


def _parse_dependency_check(path: Path) -> dict[str, Any]:
    data = _parse_json(path)
    critical = 0
    high = 0
    medium = 0
    low = 0
    if isinstance(data, dict):
        for dep in data.get("dependencies", []) or []:
            for vuln in dep.get("vulnerabilities", []) or []:
                severity = str(vuln.get("severity", "")).upper()
                if severity == "CRITICAL":
                    critical += 1
                elif severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                elif severity == "LOW":
                    low += 1
    return {
        "owasp_critical": critical,
        "owasp_high": high,
        "owasp_medium": medium,
        "owasp_low": low,
    }


def run_pytest(workdir: Path, output_dir: Path, fail_fast: bool = False) -> ToolResult:
    junit_path = output_dir / "pytest-junit.xml"
    coverage_path = output_dir / "coverage.xml"
    cmd = [
        "pytest",
        "--cov=.",
        f"--cov-report=xml:{coverage_path}",
        f"--junitxml={junit_path}",
        "-v",
    ]
    if fail_fast:
        cmd.append("-x")
    proc = _run_command(cmd, workdir)
    metrics = {}
    metrics.update(_parse_junit(junit_path))
    metrics.update(_parse_coverage(coverage_path))
    return ToolResult(
        tool="pytest",
        ran=True,
        success=proc.returncode == 0,
        metrics=metrics,
        artifacts={
            "junit": str(junit_path),
            "coverage": str(coverage_path),
        },
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_ruff(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "ruff-report.json"
    cmd = ["ruff", "check", ".", "--output-format", "json"]
    proc = _run_command(cmd, workdir)
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")
    data = _parse_json(report_path)
    parse_ok = data is not None
    errors = len(data) if isinstance(data, list) else 0
    security = 0
    if isinstance(data, list):
        security = sum(1 for item in data if str(item.get("code", "")).startswith("S"))
    return ToolResult(
        tool="ruff",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "ruff_errors": errors,
            "ruff_security": security,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_black(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "black-output.txt"
    cmd = ["black", "--check", "."]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    issues = len(re.findall(r"would reformat", proc.stdout + proc.stderr))
    return ToolResult(
        tool="black",
        ran=True,
        success=proc.returncode == 0,
        metrics={"black_issues": issues},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_isort(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "isort-output.txt"
    cmd = ["isort", "--check-only", "--diff", "."]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    issues = len(re.findall(r"^ERROR:", proc.stdout, flags=re.MULTILINE))
    return ToolResult(
        tool="isort",
        ran=True,
        success=proc.returncode == 0,
        metrics={"isort_issues": issues},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_mypy(workdir: Path, output_dir: Path) -> ToolResult:
    log_path = output_dir / "mypy-output.txt"
    cmd = ["mypy", ".", "--ignore-missing-imports"]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    errors = len(re.findall(r"\berror:", proc.stdout))
    return ToolResult(
        tool="mypy",
        ran=True,
        success=proc.returncode == 0,
        metrics={"mypy_errors": errors},
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_bandit(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "bandit-report.json"
    cmd = ["bandit", "-r", ".", "-f", "json", "-o", str(report_path)]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    results = data.get("results", []) if isinstance(data, dict) else []
    high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
    medium = sum(1 for item in results if item.get("issue_severity") == "MEDIUM")
    low = sum(1 for item in results if item.get("issue_severity") == "LOW")
    return ToolResult(
        tool="bandit",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "bandit_high": high,
            "bandit_medium": medium,
            "bandit_low": low,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _count_pip_audit_vulns(data: Any) -> int:
    if isinstance(data, list):
        total = 0
        for item in data:
            vulns = item.get("vulns") or item.get("vulnerabilities") or []
            total += len(vulns)
        return total
    return 0


def run_pip_audit(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "pip-audit-report.json"
    cmd = ["pip-audit", "--format=json", "--output", str(report_path)]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    vulns = _count_pip_audit_vulns(data)
    return ToolResult(
        tool="pip_audit",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"pip_audit_vulns": vulns, "parse_error": not parse_ok},
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _detect_mutmut_paths(workdir: Path) -> str:
    src_dir = workdir / "src"
    if src_dir.exists():
        return "src/"
    for entry in workdir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name in {"tests", "test", "venv", ".venv", "build", "dist"}:
            continue
        if (entry / "__init__.py").exists():
            return f"{entry.name}/"
    return "."


def _ensure_mutmut_config(workdir: Path) -> tuple[Path | None, str | None]:
    pyproject = workdir / "pyproject.toml"
    if pyproject.exists() and "[tool.mutmut]" in pyproject.read_text(encoding="utf-8"):
        return None, None
    setup_cfg = workdir / "setup.cfg"
    if setup_cfg.exists() and "[mutmut]" in setup_cfg.read_text(encoding="utf-8"):
        return None, None

    mutate_path = _detect_mutmut_paths(workdir)
    snippet = f"\n[mutmut]\npaths_to_mutate={mutate_path}\n"
    if setup_cfg.exists():
        original_text = setup_cfg.read_text(encoding="utf-8")
        setup_cfg.write_text(original_text + snippet, encoding="utf-8")
    else:
        original_text = None
        setup_cfg.write_text(snippet.lstrip(), encoding="utf-8")
    return setup_cfg, original_text


def run_mutmut(workdir: Path, output_dir: Path, timeout_seconds: int) -> ToolResult:
    log_path = output_dir / "mutmut-run.log"
    config_path, original = _ensure_mutmut_config(workdir)
    proc = None
    try:
        proc = _run_command(
            ["mutmut", "run"],
            workdir,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout
        if isinstance(stdout, bytes):
            stdout_text = stdout.decode("utf-8", errors="replace")
        else:
            stdout_text = stdout or ""
        log_path.write_text(stdout_text, encoding="utf-8")
        return ToolResult(
            tool="mutmut",
            ran=True,
            success=False,
            metrics={"mutation_score": 0, "mutation_killed": 0, "mutation_survived": 0},
            artifacts={"log": str(log_path)},
        )
    finally:
        if config_path:
            if original is None:
                config_path.unlink(missing_ok=True)
            else:
                config_path.write_text(original, encoding="utf-8")

    log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    results_proc = _run_command(["mutmut", "results"], workdir)
    results_text = (results_proc.stdout or "") + (results_proc.stderr or "")
    killed = len(re.findall(r"\bkilled\b", results_text, flags=re.IGNORECASE))
    survived = len(re.findall(r"\bsurvived\b", results_text, flags=re.IGNORECASE))
    total = killed + survived
    score = int(round((killed / total) * 100)) if total > 0 else 0
    return ToolResult(
        tool="mutmut",
        ran=True,
        success=proc.returncode == 0,
        metrics={
            "mutation_score": score,
            "mutation_killed": killed,
            "mutation_survived": survived,
        },
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_semgrep(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "semgrep-report.json"
    cmd = ["semgrep", "--config=auto", "--json", "--output", str(report_path), "."]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    findings = 0
    if isinstance(data, dict):
        findings = len(data.get("results", []) or [])
    return ToolResult(
        tool="semgrep",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"semgrep_findings": findings, "parse_error": not parse_ok},
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_trivy(workdir: Path, output_dir: Path) -> ToolResult:
    report_path = output_dir / "trivy-report.json"
    cmd = ["trivy", "fs", "--format", "json", "--output", str(report_path), "."]
    proc = _run_command(cmd, workdir)
    data = _parse_json(report_path)
    parse_ok = data is not None
    critical = 0
    high = 0
    medium = 0
    low = 0
    if isinstance(data, dict):
        for result in data.get("Results", []) or []:
            for vuln in result.get("Vulnerabilities", []) or []:
                severity = vuln.get("Severity")
                if severity == "CRITICAL":
                    critical += 1
                elif severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                elif severity == "LOW":
                    low += 1
    return ToolResult(
        tool="trivy",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={
            "trivy_critical": critical,
            "trivy_high": high,
            "trivy_medium": medium,
            "trivy_low": low,
            "parse_error": not parse_ok,
        },
        artifacts={"report": str(report_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _resolve_docker_compose_command() -> list[str]:
    try:
        docker_bin = resolve_executable("docker")
        return [docker_bin, "compose"]
    except FileNotFoundError:
        docker_compose = resolve_executable("docker-compose")
        return [docker_compose]


def _parse_compose_port(value: object) -> int | None:
    if isinstance(value, dict):
        published = value.get("published")
        if isinstance(published, int):
            return published
        if isinstance(published, str) and published.isdigit():
            return int(published)
        return None
    if isinstance(value, str):
        base = value.split("/")[0]
        parts = base.split(":")
        if len(parts) < 2:
            return None
        host = parts[-2]
        if host.isdigit():
            return int(host)
    return None


def _parse_compose_ports(compose_path: Path) -> list[int]:
    try:
        data = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    services = data.get("services")
    if not isinstance(services, dict):
        return []
    ports: list[int] = []
    for service in services.values():
        if not isinstance(service, dict):
            continue
        for port in service.get("ports", []) or []:
            host_port = _parse_compose_port(port)
            if host_port is not None:
                ports.append(host_port)
    return ports


def _wait_for_health(ports: list[int], endpoint: str, timeout_seconds: int) -> bool:
    if not ports:
        return False
    deadline = time.monotonic() + max(timeout_seconds, 0)
    interval = 5
    while time.monotonic() < deadline:
        for port in ports:
            url = f"http://localhost:{port}{endpoint}"
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 - local health check
                    if 200 <= resp.status < 400:
                        return True
            except Exception:  # noqa: S112 - expected failures during health poll
                continue
        time.sleep(interval)
    return False


def run_docker(
    workdir: Path,
    output_dir: Path,
    compose_file: str = "docker-compose.yml",
    health_endpoint: str | None = None,
    health_timeout: int = 300,
) -> ToolResult:
    compose_path = workdir / compose_file
    if not compose_path.exists():
        return ToolResult(
            tool="docker",
            ran=False,
            success=False,
            metrics={"docker_missing_compose": True},
        )

    compose_cmd = _resolve_docker_compose_command()
    compose_args = [*compose_cmd, "-f", str(compose_path)]
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "docker-compose.log"
    proc_up = _run_command([*compose_args, "up", "-d"], workdir)
    ran = True
    success = proc_up.returncode == 0
    health_ok = None

    if success and health_endpoint:
        endpoint = health_endpoint.strip()
        if endpoint and not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        ports = _parse_compose_ports(compose_path)
        health_ok = _wait_for_health(ports, endpoint, int(health_timeout))
        success = success and health_ok

    proc_logs = _run_command([*compose_args, "logs", "--no-color"], workdir)
    log_contents = f"{proc_logs.stdout or ''}{proc_logs.stderr or ''}"
    if log_contents:
        log_path.write_text(log_contents, encoding="utf-8")

    _run_command([*compose_args, "down", "--remove-orphans"], workdir)

    metrics: dict[str, Any] = {"docker_missing_compose": False}
    if health_endpoint:
        metrics["docker_health_ok"] = bool(health_ok)
    return ToolResult(
        tool="docker",
        ran=ran,
        success=success,
        metrics=metrics,
        artifacts={"log": str(log_path)} if log_path.exists() else {},
        stdout=proc_up.stdout,
        stderr=proc_up.stderr,
    )


def _normalize_sbom_format(format_value: str | None) -> tuple[str, str]:
    raw = (format_value or "cyclonedx").strip().lower()
    if not raw:
        raw = "cyclonedx"
    mapping = {
        "cyclonedx": "cyclonedx-json",
        "cyclonedx-json": "cyclonedx-json",
        "cyclonedxjson": "cyclonedx-json",
        "spdx": "spdx-json",
        "spdx-json": "spdx-json",
        "spdxjson": "spdx-json",
    }
    syft_format = mapping.get(raw, raw)
    if syft_format.startswith("spdx"):
        suffix = "spdx"
    elif syft_format.startswith("cyclonedx"):
        suffix = "cyclonedx"
    else:
        suffix = re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or "sbom"
    return syft_format, suffix


def run_sbom(workdir: Path, output_dir: Path, format_value: str | None = None) -> ToolResult:
    syft_format, suffix = _normalize_sbom_format(format_value)
    output_path = output_dir / f"sbom.{suffix}.json"
    cmd = ["syft", "dir:.", "-o", syft_format]
    proc = _run_command(cmd, workdir)
    if proc.stdout:
        output_path.write_text(proc.stdout, encoding="utf-8")
    parse_ok = _parse_json(output_path) is not None
    return ToolResult(
        tool="sbom",
        ran=True,
        success=proc.returncode == 0 and parse_ok,
        metrics={"parse_error": not parse_ok},
        artifacts={"sbom": str(output_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _maven_cmd(workdir: Path) -> list[str]:
    mvnw = workdir / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | 0o111)
        return ["./mvnw"]
    return ["mvn"]


def _gradle_cmd(workdir: Path) -> list[str]:
    gradlew = workdir / "gradlew"
    if gradlew.exists():
        gradlew.chmod(gradlew.stat().st_mode | 0o111)
        return ["./gradlew"]
    return ["gradle"]


def run_java_build(
    workdir: Path,
    output_dir: Path,
    build_tool: str,
    jacoco_enabled: bool,
) -> ToolResult:
    log_path = output_dir / "java-build.log"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["test", "--continue"]
        if jacoco_enabled:
            cmd.append("jacocoTestReport")
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "-Dmaven.test.failure.ignore=true",
            "verify",
        ]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    junit_paths = _find_files(
        workdir,
        [
            "target/surefire-reports/*.xml",
            "target/failsafe-reports/*.xml",
            "build/test-results/test/*.xml",
        ],
    )
    metrics = _parse_junit_files(junit_paths)
    if jacoco_enabled:
        jacoco_paths = _find_files(
            workdir,
            [
                "target/site/jacoco/jacoco.xml",
                "build/reports/jacoco/test/jacocoTestReport.xml",
            ],
        )
        metrics.update(_parse_jacoco_files(jacoco_paths))

    return ToolResult(
        tool="build",
        ran=True,
        success=proc.returncode == 0,
        metrics=metrics,
        artifacts={"log": str(log_path)},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_jacoco(workdir: Path, output_dir: Path) -> ToolResult:
    report_paths = _find_files(
        workdir,
        [
            "target/site/jacoco/jacoco.xml",
            "build/reports/jacoco/test/jacocoTestReport.xml",
        ],
    )
    metrics = _parse_jacoco_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="jacoco",
        ran=ran,
        success=ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
    )


def run_pitest(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "pitest-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["pitest", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "org.pitest:pitest-maven:mutationCoverage",
        ]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = _find_files(
        workdir,
        [
            "target/pit-reports/**/mutations.xml",
            "build/reports/pitest/mutations.xml",
        ],
    )
    metrics = _parse_pitest_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="pitest",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_checkstyle(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "checkstyle-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["checkstyleMain", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "-DskipTests",
            "checkstyle:checkstyle",
        ]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = _find_files(workdir, ["checkstyle-result.xml"])
    metrics = _parse_checkstyle_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="checkstyle",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_spotbugs(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "spotbugs-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["spotbugsMain", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + ["-B", "-ntp", "spotbugs:spotbugs"]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = _find_files(workdir, ["spotbugsXml.xml"])
    metrics = _parse_spotbugs_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="spotbugs",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_pmd(workdir: Path, output_dir: Path, build_tool: str) -> ToolResult:
    log_path = output_dir / "pmd-output.txt"
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["pmdMain", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + ["-B", "-ntp", "pmd:check"]
    proc = _run_command(cmd, workdir)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = _find_files(workdir, ["pmd.xml"])
    metrics = _parse_pmd_files(report_paths)
    ran = bool(report_paths)
    return ToolResult(
        tool="pmd",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_owasp(
    workdir: Path,
    output_dir: Path,
    build_tool: str,
    use_nvd_api_key: bool,
) -> ToolResult:
    log_path = output_dir / "owasp-output.txt"
    env = os.environ.copy()
    nvd_key = env.get("NVD_API_KEY")
    nvd_flags: list[str] = []
    if use_nvd_api_key and nvd_key:
        nvd_flags.append(f"-DnvdApiKey={nvd_key}")
    if build_tool == "gradle":
        cmd = _gradle_cmd(workdir) + ["dependencyCheckAnalyze", "--continue"]
    else:
        cmd = _maven_cmd(workdir) + [
            "-B",
            "-ntp",
            "org.owasp:dependency-check-maven:check",
            "-DfailBuildOnCVSS=11",
            "-DnvdApiDelay=2500",
            "-DnvdMaxRetryCount=10",
            "-Ddependencycheck.failOnError=false",
            *nvd_flags,
        ]
    proc = _run_command(cmd, workdir, env=env)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    report_paths = _find_files(
        workdir,
        [
            "dependency-check-report.json",
            "target/dependency-check-report.json",
            "build/reports/dependency-check-report.json",
        ],
    )
    metrics = (
        _parse_dependency_check(report_paths[0])
        if report_paths
        else {
            "owasp_critical": 0,
            "owasp_high": 0,
            "owasp_medium": 0,
            "owasp_low": 0,
        }
    )
    ran = bool(report_paths)
    return ToolResult(
        tool="owasp",
        ran=ran,
        success=proc.returncode == 0 and ran,
        metrics=metrics,
        artifacts={"report": str(report_paths[0])} if report_paths else {},
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
